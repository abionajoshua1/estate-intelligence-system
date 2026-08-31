import { useMemo, useState } from "react";
import {
  useProperties,
  useCreateProperty,
  useUpdateProperty,
  useDeleteProperty,
} from "@/hooks/useProperties";
import { useEstates } from "@/hooks/useEstates";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Building2,
  Search,
  Plus,
  MoreHorizontal,
  Pencil,
  Trash2,
  Home,
  Wrench,
  CheckCircle2,
  AlertTriangle,
  Landmark,
  User,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Confirmed data model for the Property entity:
// property_id, property_number, property_type, bedrooms, bathrooms, status,
// estate_id, estate_name, resident_id, resident_name, created_at.
// Field access is direct — no alias guessing needed.
// ---------------------------------------------------------------------------
const STATUS_OPTIONS = ["Available", "Occupied", "Maintenance"];
const TYPE_OPTIONS = ["Apartment", "Duplex", "Bungalow", "Studio"];

const getId = (p) => p?.property_id;
const getNumber = (p) => p?.property_number ?? "—";
const getType = (p) => p?.property_type ?? "—";
const getStatus = (p) => p?.status ?? "—";
const getBedrooms = (p) => p?.bedrooms;
const getBathrooms = (p) => p?.bathrooms;
const getEstateId = (p) => p?.estate_id;
const getEstateName = (p) => p?.estate_name ?? "—";
const getResidentName = (p) => p?.resident_name ?? "Unoccupied";

const getArray = (data) => {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.results)) return data.results;
  if (Array.isArray(data.properties)) return data.properties;
  if (Array.isArray(data.estates)) return data.estates;
  if (Array.isArray(data.data)) return data.data;
  return [];
};

const statusBadgeVariant = (status) => {
  const s = String(status).toLowerCase();
  if (s === "available") return "success";
  if (s === "occupied") return "secondary";
  if (s === "maintenance") return "warning";
  return "default";
};

const emptyForm = {
  estate_id: "",
  property_number: "",
  property_type: "",
  status: "",
  bedrooms: "",
  bathrooms: "",
};

export default function Properties() {
  const { data, isLoading, isError, error } = useProperties();
  const { data: estatesData, isLoading: estatesLoading } = useEstates();

  const createMutation = useCreateProperty();
  const updateMutation = useUpdateProperty();
  const deleteMutation = useDeleteProperty();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");

  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [activeProperty, setActiveProperty] = useState(null);
  const [form, setForm] = useState(emptyForm);

  const properties = useMemo(() => getArray(data), [data]);
  const estates = useMemo(() => getArray(estatesData), [estatesData]);

  const filteredProperties = useMemo(() => {
    return properties.filter((p) => {
      const q = search.trim().toLowerCase();
      const matchesSearch =
        q === "" ||
        String(getNumber(p)).toLowerCase().includes(q) ||
        String(getEstateName(p)).toLowerCase().includes(q) ||
        String(getResidentName(p)).toLowerCase().includes(q);
      const matchesStatus = statusFilter === "all" || getStatus(p) === statusFilter;
      const matchesType = typeFilter === "all" || getType(p) === typeFilter;
      return matchesSearch && matchesStatus && matchesType;
    });
  }, [properties, search, statusFilter, typeFilter]);

  const stats = useMemo(() => {
    const total = properties.length;
    const available = properties.filter((p) => getStatus(p) === "Available").length;
    const occupied = properties.filter((p) => getStatus(p) === "Occupied").length;
    const maintenance = properties.filter((p) => getStatus(p) === "Maintenance").length;
    return { total, available, occupied, maintenance };
  }, [properties]);

  const resetForm = () => setForm(emptyForm);

  const openCreate = () => {
    resetForm();
    setCreateOpen(true);
  };

  const openEdit = (property) => {
    setActiveProperty(property);
    setForm({
      estate_id: property.estate_id ?? "",
      property_number: property.property_number ?? "",
      property_type: property.property_type ?? "",
      status: property.status ?? "",
      bedrooms: property.bedrooms ?? "",
      bathrooms: property.bathrooms ?? "",
    });
    setEditOpen(true);
  };

  const openDelete = (property) => {
    setActiveProperty(property);
    setDeleteOpen(true);
  };

  const handleCreateSubmit = (e) => {
    e.preventDefault();
    createMutation.mutate(form, {
      onSuccess: () => {
        setCreateOpen(false);
        resetForm();
      },
    });
  };

  const handleEditSubmit = (e) => {
    e.preventDefault();
    if (!activeProperty) return;
    updateMutation.mutate(
      { propertyId: getId(activeProperty), data: form },
      {
        onSuccess: () => {
          setEditOpen(false);
          setActiveProperty(null);
        },
      }
    );
  };

  const handleDeleteConfirm = () => {
    if (!activeProperty) return;
    deleteMutation.mutate(getId(activeProperty), {
      onSuccess: () => {
        setDeleteOpen(false);
        setActiveProperty(null);
      },
    });
  };

  const hasActiveFilters =
    search.trim() !== "" || statusFilter !== "all" || typeFilter !== "all";

  const clearFilters = () => {
    setSearch("");
    setStatusFilter("all");
    setTypeFilter("all");
  };

  return (
    <div className="flex flex-col gap-6 p-4 sm:p-6 lg:p-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Properties</h1>
          <p className="text-sm text-muted-foreground">
            Manage properties across your estates and track their status.
          </p>
        </div>
        <Button onClick={openCreate} className="gap-2 w-full sm:w-auto">
          <Plus className="h-4 w-4" />
          Add property
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          icon={<Building2 className="h-4 w-4" />}
          label="Total properties"
          value={isLoading ? "—" : stats.total}
        />
        <StatCard
          icon={<Home className="h-4 w-4" />}
          label="Available"
          value={isLoading ? "—" : stats.available}
        />
        <StatCard
          icon={<CheckCircle2 className="h-4 w-4" />}
          label="Occupied"
          value={isLoading ? "—" : stats.occupied}
        />
        <StatCard
          icon={<Wrench className="h-4 w-4" />}
          label="Maintenance"
          value={isLoading ? "—" : stats.maintenance}
        />
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="flex flex-col gap-3 pt-6 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by property number, estate, or resident..."
              className="pl-9"
            />
          </div>

          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-full sm:w-44">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              {STATUS_OPTIONS.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-full sm:w-44">
              <SelectValue placeholder="Property type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              {TYPE_OPTIONS.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {hasActiveFilters && (
            <Button variant="ghost" onClick={clearFilters}>
              Clear filters
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <LoadingState />
          ) : isError ? (
            <ErrorState message={error?.message} />
          ) : filteredProperties.length === 0 ? (
            <EmptyState
              hasFilters={hasActiveFilters}
              onCreate={openCreate}
              onClearFilters={clearFilters}
            />
          ) : (
            <ScrollArea className="w-full">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Property Number</TableHead>
                    <TableHead className="hidden md:table-cell">Estate</TableHead>
                    <TableHead className="hidden md:table-cell">Property Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="hidden sm:table-cell">Bedrooms</TableHead>
                    <TableHead className="hidden sm:table-cell">Bathrooms</TableHead>
                    <TableHead className="hidden lg:table-cell">Resident</TableHead>
                    <TableHead className="w-10">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredProperties.map((property) => {
                    const id = getId(property);
                    return (
                      <TableRow key={id ?? getNumber(property)}>
                        <TableCell className="font-medium">
                          {getNumber(property)}
                        </TableCell>
                        <TableCell className="hidden md:table-cell">
                          {getEstateName(property)}
                        </TableCell>
                        <TableCell className="hidden md:table-cell">
                          {getType(property)}
                        </TableCell>
                        <TableCell>
                          <Badge variant={statusBadgeVariant(getStatus(property))}>
                            {getStatus(property)}
                          </Badge>
                        </TableCell>
                        <TableCell className="hidden sm:table-cell">
                          {getBedrooms(property) ?? "—"}
                        </TableCell>
                        <TableCell className="hidden sm:table-cell">
                          {getBathrooms(property) ?? "—"}
                        </TableCell>
                        <TableCell className="hidden lg:table-cell">
                          <span
                            className={
                              property.resident_name
                                ? "text-foreground"
                                : "text-muted-foreground"
                            }
                          >
                            {getResidentName(property)}
                          </span>
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem 
                                onSelect={(event) => {
                                  event.preventDefault();

                                  setTimeout(() => {
                                    openEdit(property);
                                  }, 0);
                                }}
                              >
                                <Pencil className="mr-2 h-4 w-4" />
                                Edit
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onSelect={(event) => {
                                  event.preventDefault();

                                  setTimeout(() => {
                                    openDelete(property);
                                  }, 0);
                                }}
                                className="text-destructive"
                              >
                                <Trash2 className="mr-2 h-4 w-4" />
                                Delete
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      {/* Create dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add property</DialogTitle>
          </DialogHeader>
          <PropertyForm
            form={form}
            setForm={setForm}
            onSubmit={handleCreateSubmit}
            estates={estates}
            estatesLoading={estatesLoading}
          >
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setCreateOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Creating..." : "Create property"}
              </Button>
            </DialogFooter>
          </PropertyForm>
        </DialogContent>
      </Dialog>

      {/* Edit dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit property</DialogTitle>
          </DialogHeader>
          <PropertyForm
            form={form}
            setForm={setForm}
            onSubmit={handleEditSubmit}
            estates={estates}
            estatesLoading={estatesLoading}
          >
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setEditOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? "Saving..." : "Save changes"}
              </Button>
            </DialogFooter>
          </PropertyForm>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation dialog */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete property</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Are you sure you want to delete{" "}
            <span className="font-medium text-foreground">
              {activeProperty ? getNumber(activeProperty) : "this property"}
            </span>
            ? This action cannot be undone.
          </p>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setDeleteOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function StatCard({ icon, label, value }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {label}
        </CardTitle>
        <span className="text-muted-foreground">{icon}</span>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold">{value}</div>
      </CardContent>
    </Card>
  );
}

function PropertyForm({ form, setForm, onSubmit, children, estates, estatesLoading }) {
  const update = (key) => (e) =>
    setForm((prev) => ({ ...prev, [key]: e.target.value }));

  const updateSelect = (key) => (value) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <label className="text-sm font-medium">Estate</label>

          <select
            value={form.estate_id}
            onChange={(e) =>
              setForm((prev) => ({
                ...prev,
                estate_id: e.target.value,
              }))
            }
            required
            disabled={estatesLoading}
            className="h-8 w-full rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none focus:border-ring focus:ring-3 focus:ring-ring/50"
          >
            <option value="">
              {estatesLoading ? "Loading estates..." : "Select estate"}
            </option>

            {estates.map((estate) => (
              <option
                key={estate.estate_id}
                value={estate.estate_id}
              >
                {estate.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <label className="text-sm font-medium">Property Number</label>
          <Input
            value={form.property_number}
            onChange={update("property_number")}
            placeholder="e.g. A101"
            required
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium">Property Type</label>

          <select
            value={form.property_type}
            onChange={(e) =>
              setForm((prev) => ({
                ...prev,
                property_type: e.target.value,
              }))
            }
            required
            className="h-8 w-full rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none focus:border-ring focus:ring-3 focus:ring-ring/50"
          >
            <option value="">Select type</option>

            {TYPE_OPTIONS.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium">Status</label>
          <select
            value={form.status}
            onChange={(e) =>
              setForm((prev) => ({
                ...prev,
                status: e.target.value,
              }))
            }
            required
            className="h-8 w-full rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none focus:border-ring focus:ring-3 focus:ring-ring/50"
          >
            <option value="">Select status</option>

            {STATUS_OPTIONS.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium">Bedrooms</label>
          <Input
            type="number"
            min="0"
            value={form.bedrooms}
            onChange={update("bedrooms")}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium">Bathrooms</label>
          <Input
            type="number"
            min="0"
            value={form.bathrooms}
            onChange={update("bathrooms")}
          />
        </div>
      </div>
      {children}
    </form>
  );
}

function LoadingState() {
  return (
    <div className="flex flex-col gap-3 p-6">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="h-12 w-full animate-pulse rounded-md bg-muted"
        />
      ))}
    </div>
  );
}

function ErrorState({ message }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 p-12 text-center">
      <AlertTriangle className="h-8 w-8 text-destructive" />
      <p className="font-medium">Couldn't load properties</p>
      <p className="text-sm text-muted-foreground">
        {message || "Something went wrong while fetching your properties."}
      </p>
    </div>
  );
}

function EmptyState({ hasFilters, onCreate, onClearFilters }) {
  if (hasFilters) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 p-12 text-center">
        <Building2 className="h-8 w-8 text-muted-foreground" />
        <p className="font-medium">No properties match your filters</p>
        <p className="text-sm text-muted-foreground">
          Try adjusting your search or filters.
        </p>
        <Button variant="outline" onClick={onClearFilters} className="mt-2">
          Clear filters
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center gap-2 p-12 text-center">
      <Building2 className="h-8 w-8 text-muted-foreground" />
      <p className="font-medium">No properties yet</p>
      <p className="text-sm text-muted-foreground">
        Add your first property to get started.
      </p>
      <Button onClick={onCreate} className="mt-2 gap-2">
        <Plus className="h-4 w-4" />
        Add property
      </Button>
    </div>
  );
}