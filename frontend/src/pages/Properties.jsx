import { useMemo, useState } from "react";
import {
  useProperties,
  useCreateProperty,
  useUpdateProperty,
  useDeleteProperty,
} from "@/hooks/useProperties";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
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
  DollarSign,
  Layers,
  AlertTriangle,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Helpers: the API shape isn't guaranteed field-for-field, so we resolve
// common aliases defensively instead of hardcoding a single schema.
// ---------------------------------------------------------------------------
const pick = (obj, keys, fallback = undefined) => {
  for (const key of keys) {
    if (obj && obj[key] !== undefined && obj[key] !== null && obj[key] !== "") {
      return obj[key];
    }
  }
  return fallback;
};

const getId = (p) => pick(p, ["id", "property_id", "uuid", "_id"]);
const getName = (p) => pick(p, ["name", "title", "property_name"], "Untitled property");
const getAddress = (p) =>
  pick(p, ["address", "full_address", "location", "street_address"], "—");
const getStatus = (p) => pick(p, ["status", "state", "property_status"], "unknown");
const getType = (p) => pick(p, ["type", "property_type", "category"], "unknown");
const getPrice = (p) => pick(p, ["price", "rent", "amount", "listing_price"]);
const getBedrooms = (p) => pick(p, ["bedrooms", "beds", "num_bedrooms"]);
const getBathrooms = (p) => pick(p, ["bathrooms", "baths", "num_bathrooms"]);
const getArea = (p) => pick(p, ["area", "sqft", "square_feet", "size"]);

const getPropertiesArray = (data) => {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.results)) return data.results;
  if (Array.isArray(data.properties)) return data.properties;
  if (Array.isArray(data.data)) return data.data;
  return [];
};

const formatPrice = (value) => {
  if (value === undefined || value === null || value === "") return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return String(value);
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "NGN",
    maximumFractionDigits: 0,
  }).format(num);
};

const titleCase = (str) =>
  typeof str === "string" && str.length
    ? str.replace(/[_-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
    : "Unknown";

const statusBadgeVariant = (status) => {
  const s = String(status).toLowerCase();
  if (["active", "available", "listed"].includes(s)) return "success";
  if (["pending", "under_offer", "under-offer"].includes(s)) return "warning";
  if (["sold", "leased", "rented", "closed"].includes(s)) return "secondary";
  if (["inactive", "archived", "off_market"].includes(s)) return "outline";
  return "default";
};

const emptyForm = {
  name: "",
  address: "",
  type: "",
  status: "",
  price: "",
  bedrooms: "",
  bathrooms: "",
  area: "",
};

export default function Properties() {
  const { data, isLoading, isError, error } = useProperties();

  // TODO: confirm these mutation hooks exist with this exact signature in useProperties.js
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

  const properties = useMemo(() => getPropertiesArray(data), [data]);

  const statusOptions = useMemo(() => {
    const set = new Set(properties.map((p) => getStatus(p)).filter(Boolean));
    return Array.from(set);
  }, [properties]);

  const typeOptions = useMemo(() => {
    const set = new Set(properties.map((p) => getType(p)).filter(Boolean));
    return Array.from(set);
  }, [properties]);

  const filteredProperties = useMemo(() => {
    return properties.filter((p) => {
      const matchesSearch =
        search.trim() === "" ||
        getName(p).toLowerCase().includes(search.toLowerCase()) ||
        getAddress(p).toLowerCase().includes(search.toLowerCase());
      const matchesStatus =
        statusFilter === "all" || getStatus(p) === statusFilter;
      const matchesType = typeFilter === "all" || getType(p) === typeFilter;
      return matchesSearch && matchesStatus && matchesType;
    });
  }, [properties, search, statusFilter, typeFilter]);

  const stats = useMemo(() => {
    const total = properties.length;
    const active = properties.filter((p) =>
      ["active", "available", "listed"].includes(String(getStatus(p)).toLowerCase())
    ).length;
    const pending = properties.filter((p) =>
      ["pending", "under_offer", "under-offer"].includes(
        String(getStatus(p)).toLowerCase()
      )
    ).length;
    const prices = properties
      .map((p) => Number(getPrice(p)))
      .filter((n) => !Number.isNaN(n));
    const avgPrice = prices.length
      ? prices.reduce((a, b) => a + b, 0) / prices.length
      : null;

    return { total, active, pending, avgPrice };
  }, [properties]);

  const resetForm = () => setForm(emptyForm);

  const openCreate = () => {
    resetForm();
    setCreateOpen(true);
  };

  const openEdit = (property) => {
    setActiveProperty(property);
    setForm({
      name: getName(property) ?? "",
      address: getAddress(property) === "—" ? "" : getAddress(property),
      type: getType(property) === "unknown" ? "" : getType(property),
      status: getStatus(property) === "unknown" ? "" : getStatus(property),
      price: getPrice(property) ?? "",
      bedrooms: getBedrooms(property) ?? "",
      bathrooms: getBathrooms(property) ?? "",
      area: getArea(property) ?? "",
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

  return (
    <div className="flex flex-col gap-6 p-4 sm:p-6 lg:p-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Properties</h1>
          <p className="text-sm text-muted-foreground">
            Manage your property listings, statuses, and details.
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
          label="Active"
          value={isLoading ? "—" : stats.active}
        />
        <StatCard
          icon={<Layers className="h-4 w-4" />}
          label="Pending"
          value={isLoading ? "—" : stats.pending}
        />
        <StatCard
          icon={<DollarSign className="h-4 w-4" />}
          label="Avg. price"
          value={
            isLoading
              ? "—"
              : stats.avgPrice !== null
              ? formatPrice(stats.avgPrice)
              : "—"
          }
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
              placeholder="Search by name or address..."
              className="pl-9"
            />
          </div>

          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-full sm:w-44">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              {statusOptions.map((s) => (
                <SelectItem key={s} value={s}>
                  {titleCase(s)}
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
              {typeOptions.map((t) => (
                <SelectItem key={t} value={t}>
                  {titleCase(t)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {hasActiveFilters && (
            <Button
              variant="ghost"
              onClick={() => {
                setSearch("");
                setStatusFilter("all");
                setTypeFilter("all");
              }}
            >
              Clear
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
              onClearFilters={() => {
                setSearch("");
                setStatusFilter("all");
                setTypeFilter("all");
              }}
            />
          ) : (
            <ScrollArea className="w-full">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Property</TableHead>
                    <TableHead className="hidden md:table-cell">Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="hidden sm:table-cell">Price</TableHead>
                    <TableHead className="hidden lg:table-cell">Beds / Baths</TableHead>
                    <TableHead className="hidden lg:table-cell">Area</TableHead>
                    <TableHead className="w-10" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredProperties.map((property) => {
                    const id = getId(property);
                    return (
                      <TableRow key={id ?? getName(property)}>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="font-medium">{getName(property)}</span>
                            <span className="text-xs text-muted-foreground">
                              {getAddress(property)}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="hidden md:table-cell">
                          {titleCase(getType(property))}
                        </TableCell>
                        <TableCell>
                          <Badge variant={statusBadgeVariant(getStatus(property))}>
                            {titleCase(getStatus(property))}
                          </Badge>
                        </TableCell>
                        <TableCell className="hidden sm:table-cell">
                          {formatPrice(getPrice(property))}
                        </TableCell>
                        <TableCell className="hidden lg:table-cell">
                          {getBedrooms(property) ?? "—"} / {getBathrooms(property) ?? "—"}
                        </TableCell>
                        <TableCell className="hidden lg:table-cell">
                          {getArea(property) ? `${getArea(property)} sqft` : "—"}
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => openEdit(property)}>
                                <Pencil className="mr-2 h-4 w-4" />
                                Edit
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => openDelete(property)}
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
          <PropertyForm form={form} setForm={setForm} onSubmit={handleCreateSubmit}>
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
          <PropertyForm form={form} setForm={setForm} onSubmit={handleEditSubmit}>
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
              {activeProperty ? getName(activeProperty) : "this property"}
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

function PropertyForm({ form, setForm, onSubmit, children }) {
  const update = (key) => (e) =>
    setForm((prev) => ({ ...prev, [key]: e.target.value }));

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <label className="text-sm font-medium">Name</label>
          <Input value={form.name} onChange={update("name")} required />
        </div>
        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <label className="text-sm font-medium">Address</label>
          <Textarea
            value={form.address}
            onChange={update("address")}
            rows={2}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium">Type</label>
          <Input value={form.type} onChange={update("type")} />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium">Status</label>
          <Input value={form.status} onChange={update("status")} />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium">Price</label>
          <Input
            type="number"
            value={form.price}
            onChange={update("price")}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium">Area (sqft)</label>
          <Input
            type="number"
            value={form.area}
            onChange={update("area")}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium">Bedrooms</label>
          <Input
            type="number"
            value={form.bedrooms}
            onChange={update("bedrooms")}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium">Bathrooms</label>
          <Input
            type="number"
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